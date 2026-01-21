"""
Credential management for JIRA Assistant Skills.

Provides secure credential storage with multiple backends:
1. System keychain (via keyring library) - preferred
2. settings.local.json - fallback
3. Environment variables - always checked first for retrieval

Security considerations:
- Never logs or prints credentials
- Uses sanitize_error_message() from error_handler for exception messages

This module extends the BaseCredentialManager from assistant-skills-lib
to provide JIRA-specific credential handling.
"""

from __future__ import annotations

import threading
from typing import Any

from assistant_skills_lib import (
    BaseCredentialManager,
    CredentialBackend,
)
from assistant_skills_lib import CredentialNotFoundError as BaseCredentialNotFoundError

from .error_handler import (
    AuthenticationError,
    JiraError,
)
from .validators import validate_email, validate_url


class CredentialNotFoundError(JiraError):
    """Raised when credentials cannot be found in any backend."""

    def __init__(self, **kwargs: Any):
        message = "No JIRA credentials found"
        hint = "\n\nTo set up credentials, run:\n"
        hint += "  python setup.py\n\n"
        hint += "Or set environment variables:\n"
        hint += "  export JIRA_API_TOKEN='your-token'\n"
        hint += "  export JIRA_EMAIL='your-email'\n"
        hint += "  export JIRA_SITE_URL='https://your-site.atlassian.net'\n\n"
        hint += "Get an API token at:\n"
        hint += "  https://id.atlassian.com/manage-profile/security/api-tokens"
        super().__init__(message + hint, **kwargs)


class CredentialManager(BaseCredentialManager):
    """
    Manages JIRA credentials across multiple storage backends.

    Extends BaseCredentialManager to provide JIRA-specific credential handling
    while maintaining backward compatibility with tuple-based API.

    Priority for retrieval:
    1. Environment variables (JIRA_API_TOKEN, JIRA_EMAIL, JIRA_SITE_URL)
    2. System keychain (if keyring available)
    3. settings.local.json

    Priority for storage:
    1. System keychain (if keyring available)
    2. settings.local.json (fallback)
    """

    # Field mapping for backward compatibility
    # Base class uses "site_url", JIRA traditionally used "url"
    _FIELD_SITE_URL = "site_url"
    _FIELD_EMAIL = "email"
    _FIELD_API_TOKEN = "api_token"

    def get_service_name(self) -> str:
        """Return the keychain service name."""
        return "jira-assistant"

    def get_env_prefix(self) -> str:
        """Return the environment variable prefix."""
        return "JIRA"

    def get_credential_fields(self) -> list[str]:
        """Return list of credential field names."""
        return [self._FIELD_SITE_URL, self._FIELD_EMAIL, self._FIELD_API_TOKEN]

    def get_credential_not_found_hint(self) -> str:
        """Return JIRA-specific help text for credential not found error."""
        hint = "To set up credentials, run:\n"
        hint += "  python setup.py\n\n"
        hint += "Or set environment variables:\n"
        hint += "  export JIRA_API_TOKEN='your-token'\n"
        hint += "  export JIRA_EMAIL='your-email'\n"
        hint += "  export JIRA_SITE_URL='https://your-site.atlassian.net'\n\n"
        hint += "Get an API token at:\n"
        hint += "  https://id.atlassian.com/manage-profile/security/api-tokens"
        return hint

    def validate_credentials(self, credentials: dict[str, str]) -> dict[str, Any]:
        """
        Validate credentials by making a test API call.

        Args:
            credentials: Dictionary with site_url, email, api_token

        Returns:
            User info dict on success

        Raises:
            AuthenticationError: If credentials are invalid
            JiraError: If connection fails
        """
        import requests

        from .error_handler import sanitize_error_message

        url = credentials.get(self._FIELD_SITE_URL, "")
        email = credentials.get(self._FIELD_EMAIL, "")
        api_token = credentials.get(self._FIELD_API_TOKEN, "")

        # Validate URL format first
        url = validate_url(url)

        # Test with /rest/api/3/myself endpoint
        test_url = f"{url}/rest/api/3/myself"

        try:
            response = requests.get(
                test_url,
                auth=(email, api_token),
                headers={"Accept": "application/json"},
                timeout=10,
            )

            if response.status_code == 401:
                raise AuthenticationError(
                    "Invalid credentials. Please check your email and API token."
                )
            elif response.status_code == 403:
                raise AuthenticationError(
                    "Access forbidden. Your API token may lack required permissions."
                )
            elif not response.ok:
                raise JiraError(
                    f"Connection failed with status {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except requests.exceptions.ConnectionError:
            raise JiraError(
                f"Cannot connect to {url}. Please check the URL and your network connection."
            )
        except requests.exceptions.Timeout:
            raise JiraError(
                f"Connection to {url} timed out. The server may be slow or unreachable."
            )
        except requests.exceptions.RequestException as e:
            raise JiraError(f"Connection error: {sanitize_error_message(str(e))}")

    # -------------------------------------------------------------------------
    # Backward-compatible tuple-based API methods
    # These wrap the base class dict-based methods for existing code
    # -------------------------------------------------------------------------

    def get_credentials_tuple(self) -> tuple[str, str, str]:
        """
        Retrieve credentials as a tuple (url, email, api_token).

        This is the backward-compatible method for existing code.

        Returns:
            Tuple of (url, email, api_token)

        Raises:
            CredentialNotFoundError: If credentials not found in any backend
            ValidationError: If credentials are invalid
        """
        try:
            creds = self.get_credentials()
        except BaseCredentialNotFoundError:
            raise CredentialNotFoundError()

        url = creds.get(self._FIELD_SITE_URL, "")
        email = creds.get(self._FIELD_EMAIL, "")
        api_token = creds.get(self._FIELD_API_TOKEN, "")

        # Validate credentials
        url = validate_url(url)
        email = validate_email(email)

        return url, email, api_token

    def store_credentials_tuple(
        self,
        url: str,
        email: str,
        api_token: str,
        backend: CredentialBackend | None = None,
    ) -> CredentialBackend:
        """
        Store credentials from tuple values.

        This is the backward-compatible method for existing code.

        Args:
            url: JIRA site URL
            email: User email
            api_token: API token
            backend: Specific backend to use (default: auto-select best available)

        Returns:
            The backend where credentials were stored

        Raises:
            ValidationError: If credentials are invalid
            JiraError: If storage fails
        """
        from .error_handler import ValidationError

        # Validate inputs
        url = validate_url(url)
        email = validate_email(email)

        if not api_token or not api_token.strip():
            raise ValidationError("API token cannot be empty")

        credentials = {
            self._FIELD_SITE_URL: url,
            self._FIELD_EMAIL: email,
            self._FIELD_API_TOKEN: api_token,
        }

        return self.store_credentials(credentials, backend)

    def validate_credentials_tuple(
        self, url: str, email: str, api_token: str
    ) -> dict[str, Any]:
        """
        Validate credentials from tuple values.

        This is the backward-compatible method for existing code.

        Args:
            url: JIRA site URL
            email: User email
            api_token: API token

        Returns:
            User info dict on success

        Raises:
            AuthenticationError: If credentials are invalid
            JiraError: If connection fails
        """
        credentials = {
            self._FIELD_SITE_URL: url,
            self._FIELD_EMAIL: email,
            self._FIELD_API_TOKEN: api_token,
        }
        return self.validate_credentials(credentials)


# Singleton instance with thread-safe initialization
_credential_manager: CredentialManager | None = None
_credential_manager_lock = threading.Lock()


def get_credential_manager() -> CredentialManager:
    """Get or create global CredentialManager instance.

    Thread-safe singleton access using double-checked locking pattern.
    """
    global _credential_manager
    if _credential_manager is None:
        with _credential_manager_lock:
            if _credential_manager is None:
                _credential_manager = CredentialManager()
    return _credential_manager


# Convenience functions (match config_manager.py pattern)


def is_keychain_available() -> bool:
    """Check if system keychain is available."""
    return CredentialManager.is_keychain_available()


def get_credentials() -> tuple[str, str, str]:
    """
    Get JIRA credentials.

    Returns:
        Tuple of (url, email, api_token)
    """
    manager = get_credential_manager()
    return manager.get_credentials_tuple()


def store_credentials(
    url: str,
    email: str,
    api_token: str,
    backend: CredentialBackend | None = None,
) -> CredentialBackend:
    """
    Store credentials using preferred backend.

    Args:
        url: JIRA site URL
        email: User email
        api_token: API token
        backend: Specific backend to use (default: auto-select)

    Returns:
        The backend where credentials were stored
    """
    manager = get_credential_manager()
    return manager.store_credentials_tuple(url, email, api_token, backend)


def validate_credentials(url: str, email: str, api_token: str) -> dict[str, Any]:
    """
    Validate credentials by making a test API call.

    Args:
        url: JIRA site URL
        email: User email
        api_token: API token

    Returns:
        User info dict on success
    """
    manager = get_credential_manager()
    return manager.validate_credentials_tuple(url, email, api_token)

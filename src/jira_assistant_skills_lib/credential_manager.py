"""
Credential management for JIRA Assistant Skills.

Provides secure credential storage with multiple backends:
1. System keychain (via keyring library) - preferred
2. settings.local.json - fallback
3. Environment variables - always checked first for retrieval

Security considerations:
- Never logs or prints credentials
- Uses sanitize_error_message() from error_handler for exception messages
"""

from __future__ import annotations

import gc
import json
import os
import stat
from enum import Enum
from pathlib import Path
from typing import Any

from .error_handler import (
    AuthenticationError,
    JiraError,
    ValidationError,
    sanitize_error_message,
)
from .validators import validate_email, validate_url

# Try to import keyring, gracefully handle if not installed
try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class CredentialBackend(Enum):
    """Available credential storage backends."""

    KEYCHAIN = (
        "keychain"  # macOS Keychain, Windows Credential Manager, Linux Secret Service
    )
    JSON_FILE = "json_file"  # settings.local.json
    ENVIRONMENT = "environment"  # Environment variables (read-only for retrieval)


class CredentialNotFoundError(JiraError):
    """Raised when credentials cannot be found in any backend."""

    def __init__(self, **kwargs):
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


class CredentialManager:
    """
    Manages JIRA credentials across multiple storage backends.

    Priority for retrieval:
    1. Environment variables (JIRA_API_TOKEN, JIRA_EMAIL, JIRA_SITE_URL)
    2. System keychain (if keyring available)
    3. settings.local.json

    Priority for storage:
    1. System keychain (if keyring available)
    2. settings.local.json (fallback)
    """

    KEYCHAIN_SERVICE = "jira-assistant"

    def __init__(self):
        """
        Initialize credential manager.
        """
        self._claude_dir = self._find_claude_dir()

    def _find_claude_dir(self) -> Path | None:
        """
        Find .claude directory by walking up from current directory.

        Returns:
            Path to .claude directory or None if not found
        """
        current = Path.cwd()

        while current != current.parent:
            claude_dir = current / ".claude"
            if claude_dir.is_dir():
                return claude_dir
            current = current.parent

        return None

    def _get_keychain_service(self) -> str:
        """Get keychain service name."""
        return self.KEYCHAIN_SERVICE

    @staticmethod
    def is_keychain_available() -> bool:
        """
        Check if keyring is installed and functional.

        Returns:
            True if keyring is available and working, False otherwise
        """
        if not KEYRING_AVAILABLE:
            return False

        try:
            # Test keyring functionality with a dummy operation
            # This verifies the backend is properly configured
            keyring.get_keyring()
            return True
        except Exception:
            return False

    def get_credentials_from_env(self) -> tuple[str | None, str | None, str | None]:
        """
        Get credentials from environment variables.

        Returns:
            Tuple of (url, email, api_token) - any may be None if not set
        """
        url = os.getenv("JIRA_SITE_URL")
        email = os.getenv("JIRA_EMAIL")
        api_token = os.getenv("JIRA_API_TOKEN")

        return url, email, api_token

    def get_credentials_from_keychain(
        self,
    ) -> tuple[str | None, str | None, str | None]:
        """
        Get credentials from system keychain.

        Returns:
            Tuple of (url, email, api_token) - all None if not found or keychain unavailable
        """
        if not self.is_keychain_available():
            return None, None, None

        service = self._get_keychain_service()

        try:
            # We store as JSON: {"url": "...", "email": "...", "api_token": "..."}
            credential_json = keyring.get_password(service, "credentials")
            if not credential_json:
                return None, None, None

            creds = json.loads(credential_json)
            return creds.get("url"), creds.get("email"), creds.get("api_token")
        except Exception:
            return None, None, None

    def get_credentials_from_json(self) -> tuple[str | None, str | None, str | None]:
        """
        Get credentials from settings.local.json.

        Returns:
            Tuple of (url, email, api_token) - any may be None if not found
        """
        if not self._claude_dir:
            return None, None, None

        local_settings = self._claude_dir / "settings.local.json"

        if not local_settings.exists():
            return None, None, None

        try:
            with open(local_settings) as f:
                config = json.load(f)

            jira_config = config.get("jira", {})
            credentials = jira_config.get("credentials", {})

            url = credentials.get("url")
            email = credentials.get("email")
            api_token = credentials.get("api_token")

            return url, email, api_token
        except Exception:
            return None, None, None

    def get_credentials(self) -> tuple[str, str, str]:
        """
        Retrieve credentials (url, email, api_token).

        Checks in priority order:
        1. Environment variables
        2. System keychain
        3. settings.local.json

        Returns:
            Tuple of (url, email, api_token)

        Raises:
            CredentialNotFoundError: If credentials not found in any backend
            ValidationError: If credentials are invalid
        """
        # Collect credentials from all sources
        url, email, api_token = None, None, None

        # Priority 1: Environment variables (highest priority)
        env_url, env_email, env_token = self.get_credentials_from_env()
        url = url or env_url
        email = email or env_email
        api_token = api_token or env_token

        # Priority 2: Keychain (if available)
        if not (url and email and api_token):
            kc_url, kc_email, kc_token = self.get_credentials_from_keychain()
            url = url or kc_url
            email = email or kc_email
            api_token = api_token or kc_token

        # Priority 3: JSON file
        if not (url and email and api_token):
            json_url, json_email, json_token = self.get_credentials_from_json()
            url = url or json_url
            email = email or json_email
            api_token = api_token or json_token

        # Check if we have all required credentials
        if not url:
            raise CredentialNotFoundError()
        if not email:
            raise CredentialNotFoundError()
        if not api_token:
            raise CredentialNotFoundError()

        # Validate credentials
        try:
            url = validate_url(url)
            email = validate_email(email)
        except ValidationError:
            raise

        return url, email, api_token

    def store_credentials(
        self,
        url: str,
        email: str,
        api_token: str,
        backend: CredentialBackend | None = None,
    ) -> CredentialBackend:
        """
        Store credentials in the specified or preferred backend.

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
        # Validate inputs
        url = validate_url(url)
        email = validate_email(email)

        if not api_token or not api_token.strip():
            raise ValidationError("API token cannot be empty")

        # Determine backend
        if backend is None:
            if self.is_keychain_available():
                backend = CredentialBackend.KEYCHAIN
            else:
                backend = CredentialBackend.JSON_FILE

        # Store based on backend
        if backend == CredentialBackend.KEYCHAIN:
            return self._store_to_keychain(url, email, api_token)
        elif backend == CredentialBackend.JSON_FILE:
            return self._store_to_json(url, email, api_token)
        else:
            raise ValidationError(f"Cannot store to backend: {backend.value}")

    def _store_to_keychain(
        self, url: str, email: str, api_token: str
    ) -> CredentialBackend:
        """Store credentials in system keychain."""
        if not self.is_keychain_available():
            raise JiraError(
                "Keychain is not available. Install keyring: pip install keyring"
            )

        service = self._get_keychain_service()

        try:
            # Store as JSON
            credential_json = json.dumps(
                {"url": url, "email": email, "api_token": api_token}
            )
            keyring.set_password(service, "credentials", credential_json)

            # Clear sensitive data from memory
            del credential_json
            gc.collect()

            return CredentialBackend.KEYCHAIN
        except Exception as e:
            raise JiraError(
                f"Failed to store credentials in keychain: {sanitize_error_message(str(e))}"
            )

    def _store_to_json(self, url: str, email: str, api_token: str) -> CredentialBackend:
        """Store credentials in settings.local.json."""
        if not self._claude_dir:
            raise JiraError("Cannot find .claude directory. Run from project root.")

        local_settings = self._claude_dir / "settings.local.json"

        try:
            # Load existing config or create new
            if local_settings.exists():
                with open(local_settings) as f:
                    config = json.load(f)
            else:
                config = {}

            # Ensure structure exists
            if "jira" not in config:
                config["jira"] = {}
            if "credentials" not in config["jira"]:
                config["jira"]["credentials"] = {}

            # Store credentials
            config["jira"]["credentials"]["url"] = url
            config["jira"]["credentials"]["email"] = email
            config["jira"]["credentials"]["api_token"] = api_token

            # Write with secure permissions
            with open(local_settings, "w") as f:
                json.dump(config, f, indent=2)

            # Set restrictive permissions (owner read/write only)
            os.chmod(local_settings, stat.S_IRUSR | stat.S_IWUSR)

            return CredentialBackend.JSON_FILE
        except Exception as e:
            raise JiraError(
                f"Failed to store credentials in JSON: {sanitize_error_message(str(e))}"
            )

    def delete_credentials(self) -> bool:
        """
        Delete credentials from all backends.

        Returns:
            True if any credentials were deleted, False otherwise
        """
        deleted = False

        # Delete from keychain
        if self.is_keychain_available():
            service = self._get_keychain_service()
            try:
                keyring.delete_password(service, "credentials")
                deleted = True
            except Exception:
                pass  # May not exist

        # Delete from JSON
        if self._claude_dir:
            local_settings = self._claude_dir / "settings.local.json"
            if local_settings.exists():
                try:
                    with open(local_settings) as f:
                        config = json.load(f)

                    # Remove credentials
                    if "jira" in config and "credentials" in config["jira"]:
                        del config["jira"]["credentials"]
                        deleted = True

                        with open(local_settings, "w") as f:
                            json.dump(config, f, indent=2)
                except Exception:
                    pass

        return deleted

    def validate_credentials(
        self, url: str, email: str, api_token: str
    ) -> dict[str, Any]:
        """
        Validate credentials by making a test API call.

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
        import requests

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
    manager = CredentialManager()
    return manager.get_credentials()


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
    manager = CredentialManager()
    return manager.store_credentials(url, email, api_token, backend)


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
    manager = CredentialManager()
    return manager.validate_credentials(url, email, api_token)

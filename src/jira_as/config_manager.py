"""
Configuration management for JIRA Assistant Skills.

Handles loading and merging configuration from multiple sources:
1. Environment variables (highest priority)
2. System keychain (if keyring available)
3. .claude/settings.local.json (personal settings, gitignored)
4. .claude/settings.json (team defaults, committed)
5. Hardcoded defaults (fallbacks)

Supports configurable Agile field IDs with automatic discovery fallback.
"""

from __future__ import annotations

import os
from typing import Any

from assistant_skills_lib.config_manager import BaseConfigManager
from assistant_skills_lib.error_handler import (  # Assuming error_handler is consolidated next
    ValidationError,
)
from assistant_skills_lib.validators import (  # Assuming validate_url is consolidated next
    validate_url,
)

from .automation_client import AutomationClient
from .constants import DEFAULT_AGILE_FIELDS
from .jira_client import JiraClient
from .validators import (  # Keep local validate_email for now, will consolidate generic ones
    validate_email,
)

# Try to import credential_manager for keychain support
try:
    from .credential_manager import CredentialManager, is_keychain_available

    CREDENTIAL_MANAGER_AVAILABLE = True
except ImportError:
    CREDENTIAL_MANAGER_AVAILABLE = False


class ConfigManager(BaseConfigManager):
    """
    Manages JIRA configuration from multiple sources.
    """

    def __init__(self, **kwargs):
        """
        Initialize configuration manager.

        Args:
            **kwargs: Ignored for backward compatibility with base class.
        """
        super().__init__()  # Call BaseConfigManager's init

    def get_service_name(self) -> str:
        """
        Returns the name of the service, which is 'jira'.
        """
        return "jira"

    def get_default_config(self) -> dict[str, Any]:
        """
        Returns the default configuration dictionary for JIRA.
        """
        return {
            "api": {
                "version": "3",
                "timeout": 30,
                "max_retries": 3,
                "retry_backoff": 2.0,
            },
        }

    def get_credentials(self) -> tuple:
        """
        Get JIRA credentials (URL, email, API token).

        Checks in priority order:
        1. Environment variables (highest priority)
        2. System keychain (if keyring available)
        3. settings.local.json
        4. settings.json (for URL only)

        Returns:
            Tuple of (url, email, api_token)

        Raises:
            ValidationError: If required credentials are missing
        """
        # Initialize credential variables
        url, email, api_token = None, None, None

        # Priority 1: Environment variables (highest priority)
        url = self.get_credential_from_env("SITE_URL")
        email = self.get_credential_from_env("EMAIL")
        api_token = self.get_credential_from_env("API_TOKEN")

        # Priority 2: System keychain (if available and we're missing any credential)
        if CREDENTIAL_MANAGER_AVAILABLE and is_keychain_available():
            if not (url and email and api_token):
                try:
                    cred_mgr = CredentialManager()
                    kc_url, kc_email, kc_token = (
                        cred_mgr.get_credentials_from_keychain()
                    )
                    url = url or kc_url
                    email = email or kc_email
                    api_token = api_token or kc_token
                except Exception:
                    pass  # Keychain lookup failed, continue to JSON fallback

        # Priority 3: settings.local.json credentials
        if not (url and email and api_token):
            credentials = self.config.get("jira", {}).get("credentials", {})
            email = email or credentials.get("email")
            api_token = api_token or credentials.get("api_token")
            url = url or credentials.get("url")

        # Validate we have all required credentials
        if not url:
            raise ValidationError(
                "JIRA URL not configured. "
                "Set JIRA_SITE_URL environment variable, run setup.py, or configure in .claude/settings.json"
            )

        if not api_token:
            raise ValidationError(
                "JIRA API token not configured. "
                "Set JIRA_API_TOKEN environment variable, run setup.py, or configure in .claude/settings.local.json\n"
                "Get a token at: https://id.atlassian.com/manage-profile/security/api-tokens"
            )

        if not email:
            raise ValidationError(
                "JIRA email not configured. "
                "Set JIRA_EMAIL environment variable, run setup.py, or configure in .claude/settings.local.json"
            )

        # Validate format (using base class's validate_url from assistant_skills_lib)
        url = validate_url(url)
        email = validate_email(email)  # Keep local validate_email for now

        return url, email, api_token

    def get_api_config(self) -> dict[str, Any]:
        """
        Get API configuration (timeout, retries, etc.).

        Returns:
            API configuration dictionary
        """
        # Get base API config and merge with Jira-specific defaults/overrides
        base_api_config = super().get_api_config()
        jira_api_config = self.config.get(self.service_name, {}).get("api", {})
        base_api_config.update(jira_api_config)
        return base_api_config

    def get_client(self) -> JiraClient:
        """
        Create a configured JIRA client.

        Returns:
            Configured JiraClient instance

        Raises:
            ValidationError: If configuration is invalid or incomplete
        """
        url, email, api_token = self.get_credentials()
        api_config = self.get_api_config()

        return JiraClient(
            base_url=url,
            email=email,
            api_token=api_token,
            timeout=api_config.get("timeout", 30),
            max_retries=api_config.get("max_retries", 3),
            retry_backoff=api_config.get("retry_backoff", 2.0),
        )

    def get_default_project(self) -> str | None:
        """
        Get default project key from configuration.

        Returns:
            Default project key or None
        """
        return self.config.get(self.service_name, {}).get("default_project")

    def get_agile_fields(self) -> dict[str, str]:
        """
        Get Agile field IDs.

        Returns configured field IDs merged with defaults.

        Returns:
            Dictionary of field names to field IDs:
            - epic_link: Epic Link field ID
            - story_points: Story Points field ID
            - epic_name: Epic Name field ID
            - epic_color: Epic Color field ID
            - sprint: Sprint field ID
        """
        # Start with defaults
        fields = DEFAULT_AGILE_FIELDS.copy()

        # Check environment variables (highest priority)
        env_mappings = {
            "epic_link": "JIRA_EPIC_LINK_FIELD",
            "story_points": "JIRA_STORY_POINTS_FIELD",
            "epic_name": "JIRA_EPIC_NAME_FIELD",
            "epic_color": "JIRA_EPIC_COLOR_FIELD",
            "sprint": "JIRA_SPRINT_FIELD",
        }

        for field_name, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                fields[field_name] = env_value

        # Override with config file settings
        agile_config = self.config.get(self.service_name, {}).get("agile_fields", {})
        for field_name, field_id in agile_config.items():
            if field_id:
                fields[field_name] = field_id

        return fields

    def get_agile_field(self, field_name: str) -> str:
        """
        Get a specific Agile field ID.

        Args:
            field_name: Field name (epic_link, story_points, epic_name, epic_color, sprint)

        Returns:
            Field ID string

        Raises:
            ValidationError: If field_name is not a valid Agile field
        """
        valid_fields = [
            "epic_link",
            "story_points",
            "epic_name",
            "epic_color",
            "sprint",
        ]
        if field_name not in valid_fields:
            raise ValidationError(
                f"Invalid Agile field name: {field_name}. "
                f"Valid fields: {', '.join(valid_fields)}"
            )

        fields = self.get_agile_fields()
        return fields[field_name]

    def get_automation_client(self) -> AutomationClient:
        """
        Create a configured Automation API client.

        Returns:
            Configured AutomationClient instance

        Raises:
            ValidationError: If configuration is invalid or incomplete
        """
        url, email, api_token = self.get_credentials()
        api_config = self.get_api_config()

        # Check for optional automation-specific config
        automation_config = self.config.get(self.service_name, {}).get("automation", {})
        cloud_id = automation_config.get("cloudId")
        product = automation_config.get("product", "jira")
        use_gateway = automation_config.get("useGateway", False)

        return AutomationClient(
            site_url=url,
            email=email,
            api_token=api_token,
            cloud_id=cloud_id,  # Will be auto-fetched if None
            product=product,
            use_gateway=use_gateway,
            timeout=api_config.get("timeout", 30),
            max_retries=api_config.get("max_retries", 3),
            retry_backoff=api_config.get("retry_backoff", 2.0),
        )


def get_jira_client() -> "JiraClient":
    """
    Convenience function to get a configured JIRA client.

    Returns:
        Configured JiraClient instance (or MockJiraClient if JIRA_MOCK_MODE=true).
        MockJiraClient is API-compatible with JiraClient.

    Raises:
        ValidationError: If configuration is invalid or incomplete
    """
    # Check for mock mode first - allows testing without real JIRA credentials
    from .mock import MockJiraClient, is_mock_mode

    if is_mock_mode():
        return MockJiraClient()  # type: ignore[return-value]

    config_manager = ConfigManager.get_instance()
    return config_manager.get_client()


def get_automation_client() -> AutomationClient:
    """
    Convenience function to get a configured Automation API client.

    Returns:
        Configured AutomationClient instance

    Raises:
        ValidationError: If configuration is invalid or incomplete
    """
    config_manager = ConfigManager.get_instance()
    return config_manager.get_automation_client()


def get_agile_fields() -> dict[str, str]:
    """
    Convenience function to get Agile field IDs.

    Returns:
        Dictionary of field names to field IDs
    """
    config_manager = ConfigManager.get_instance()
    return config_manager.get_agile_fields()


def get_agile_field(field_name: str) -> str:
    """
    Convenience function to get a specific Agile field ID.

    Args:
        field_name: Field name (epic_link, story_points, epic_name, epic_color, sprint)

    Returns:
        Field ID string

    Raises:
        ValidationError: If field_name is not a valid Agile field
    """
    config_manager = ConfigManager.get_instance()
    return config_manager.get_agile_field(field_name)


# Project context functions - lazy imports to avoid circular dependencies
def get_project_context(project_key: str):
    """
    Convenience function to get project context.

    Lazy-loads project context from skill directory and/or settings.local.json.

    Args:
        project_key: JIRA project key (e.g., 'PROJ')

    Returns:
        ProjectContext object with metadata, workflows, patterns, and defaults
    """
    from .project_context import get_project_context as _get_project_context

    return _get_project_context(project_key)


def get_project_defaults(
    project_key: str, issue_type: str | None = None
) -> dict[str, Any]:
    """
    Convenience function to get default values for issue creation.

    Args:
        project_key: JIRA project key (e.g., 'PROJ')
        issue_type: Issue type name (e.g., 'Bug', 'Story') - if specified,
                    merges global defaults with type-specific defaults

    Returns:
        Dict with default values: priority, assignee, labels, components, etc.
        Returns empty dict if no project context exists.
    """
    from .project_context import (
        get_defaults_for_issue_type,
    )
    from .project_context import get_project_context as _get_project_context

    context = _get_project_context(project_key)

    if not context.has_context():
        return {}

    if issue_type:
        return get_defaults_for_issue_type(context, issue_type)
    else:
        return context.defaults.get("global", {})


def has_project_context(project_key: str) -> bool:
    """
    Convenience function to check if project context exists.

    Args:
        project_key: JIRA project key

    Returns:
        True if skill directory or settings config exists for this project
    """
    from .project_context import has_project_context as _has_project_context

    return _has_project_context(project_key)

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

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from assistant_skills_lib.config_manager import BaseConfigManager
from assistant_skills_lib.error_handler import (
    ValidationError,
)  # Assuming error_handler is consolidated next
from assistant_skills_lib.validators import (
    validate_url,
)  # Assuming validate_url is consolidated next

from .validators import (
    validate_email,
)  # Keep local validate_email for now, will consolidate generic ones
from .jira_client import JiraClient
from .automation_client import AutomationClient

# Try to import credential_manager for keychain support
try:
    from .credential_manager import CredentialManager, is_keychain_available

    CREDENTIAL_MANAGER_AVAILABLE = True
except ImportError:
    CREDENTIAL_MANAGER_AVAILABLE = False


# Default Agile field IDs (common defaults, may vary per JIRA instance)
DEFAULT_AGILE_FIELDS = {
    "epic_link": "customfield_10014",
    "story_points": "customfield_10016",
    "epic_name": "customfield_10011",
    "epic_color": "customfield_10012",
    "sprint": "customfield_10020",
}


class ConfigManager(BaseConfigManager):
    """
    Manages JIRA configuration from multiple sources with profile support.
    """

    def __init__(self, profile: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            profile: Profile name to use (default: from config or 'production')
        """
        super().__init__(profile=profile)  # Call BaseConfigManager's init

    def get_service_name(self) -> str:
        """
        Returns the name of the service, which is 'jira'.
        """
        return "jira"

    def get_default_config(self) -> Dict[str, Any]:
        """
        Returns the default configuration dictionary for JIRA.
        """
        return {
            "default_profile": "production",
            "profiles": {},
            "api": {
                "version": "3",
                "timeout": 30,
                "max_retries": 3,
                "retry_backoff": 2.0,
            },
        }

    def get_profile_config(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Get configuration for a specific profile.

        Args:
            profile: Profile name (default: self.profile)

        Returns:
            Profile configuration

        Raises:
            ValidationError: If profile doesn't exist
        """
        profile_name = profile or self.profile
        profiles = self.config.get(self.service_name, {}).get("profiles", {})

        if profile_name not in profiles:
            raise ValidationError(
                f"Profile '{profile_name}' not found. Available profiles: {list(profiles.keys())}"
            )

        return profiles[profile_name]

    def get_credentials(self, profile: Optional[str] = None) -> tuple:
        """
        Get JIRA credentials (URL, email, API token) for a profile.

        Checks in priority order:
        1. Environment variables (highest priority)
        2. System keychain (if keyring available)
        3. settings.local.json
        4. settings.json (for URL only)

        Args:
            profile: Profile name (default: self.profile)

        Returns:
            Tuple of (url, email, api_token)

        Raises:
            ValidationError: If required credentials are missing
        """
        profile = profile or self.profile

        # Get profile config (may raise ValidationError if profile doesn't exist)
        try:
            profile_config = self.get_profile_config(profile)
        except ValidationError:
            profile_config = {}

        # Initialize credential variables
        url, email, api_token = None, None, None

        # Priority 1: Environment variables (highest priority)
        url = self.get_credential_from_env("SITE_URL")
        email = self.get_credential_from_env("EMAIL")
        api_token = self.get_credential_from_env(
            f"API_TOKEN_{profile.upper()}"
        ) or self.get_credential_from_env("API_TOKEN")

        # Priority 2: System keychain (if available and we're missing any credential)
        if CREDENTIAL_MANAGER_AVAILABLE and is_keychain_available():
            if not (url and email and api_token):
                try:
                    cred_mgr = CredentialManager(profile)
                    kc_url, kc_email, kc_token = cred_mgr.get_credentials_from_keychain(
                        profile
                    )
                    url = url or kc_url
                    email = email or kc_email
                    api_token = api_token or kc_token
                except Exception:
                    pass  # Keychain lookup failed, continue to JSON fallback

        # Priority 3: settings.local.json credentials
        if not (url and email and api_token):
            credentials = self.config.get("jira", {}).get("credentials", {})
            profile_creds = credentials.get(profile, {})
            email = email or profile_creds.get("email")
            api_token = api_token or profile_creds.get("api_token")

        # Priority 4: settings.json for URL (from profile config)
        if not url:
            url = profile_config.get("url")

        # Validate we have all required credentials
        if not url:
            raise ValidationError(
                f"JIRA URL not configured for profile '{profile}'. "
                "Set JIRA_SITE_URL environment variable, run setup.py, or configure in .claude/settings.json"
            )

        if not api_token:
            raise ValidationError(
                f"JIRA API token not configured for profile '{profile}'. "
                "Set JIRA_API_TOKEN environment variable, run setup.py, or configure in .claude/settings.local.json\n"
                "Get a token at: https://id.atlassian.com/manage-profile/security/api-tokens"
            )

        if not email:
            raise ValidationError(
                f"JIRA email not configured for profile '{profile}'. "
                "Set JIRA_EMAIL environment variable, run setup.py, or configure in .claude/settings.local.json"
            )

        # Validate format (using base class's validate_url from assistant_skills_lib)
        url = validate_url(url)
        email = validate_email(email)  # Keep local validate_email for now

        return url, email, api_token

    def get_api_config(self) -> Dict[str, Any]:
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

    def get_client(self, profile: Optional[str] = None) -> JiraClient:
        """
        Create a configured JIRA client for a profile.

        Args:
            profile: Profile name (default: self.profile)

        Returns:
            Configured JiraClient instance

        Raises:
            ValidationError: If configuration is invalid or incomplete
        """
        profile = profile or self.profile
        url, email, api_token = self.get_credentials(profile)
        api_config = self.get_api_config()

        return JiraClient(
            base_url=url,
            email=email,
            api_token=api_token,
            timeout=api_config.get("timeout", 30),
            max_retries=api_config.get("max_retries", 3),
            retry_backoff=api_config.get("retry_backoff", 2.0),
        )

    def get_default_project(self, profile: Optional[str] = None) -> Optional[str]:
        """
        Get default project key for a profile.

        Args:
            profile: Profile name (default: self.profile)

        Returns:
            Default project key or None
        """
        profile = profile or self.profile
        try:
            profile_config = self.get_profile_config(profile)
            return profile_config.get("default_project")
        except ValidationError:
            return None

    def get_agile_fields(self, profile: Optional[str] = None) -> Dict[str, str]:
        """
        Get Agile field IDs for a profile.

        Returns configured field IDs merged with defaults.

        Args:
            profile: Profile name (default: self.profile)

        Returns:
            Dictionary of field names to field IDs:
            - epic_link: Epic Link field ID
            - story_points: Story Points field ID
            - epic_name: Epic Name field ID
            - epic_color: Epic Color field ID
            - sprint: Sprint field ID
        """
        profile = profile or self.profile

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

        # Override with profile-specific config
        try:
            profile_config = self.get_profile_config(profile)
            agile_config = profile_config.get("agile_fields", {})
            for field_name, field_id in agile_config.items():
                if field_id:
                    fields[field_name] = field_id
        except ValidationError:
            pass  # Profile doesn't exist, use defaults

        return fields

    def get_agile_field(self, field_name: str, profile: Optional[str] = None) -> str:
        """
        Get a specific Agile field ID.

        Args:
            field_name: Field name (epic_link, story_points, epic_name, epic_color, sprint)
            profile: Profile name (default: self.profile)

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

        fields = self.get_agile_fields(profile)
        return fields[field_name]

    def get_automation_client(self, profile: Optional[str] = None) -> AutomationClient:
        """
        Create a configured Automation API client for a profile.

        Args:
            profile: Profile name (default: self.profile)

        Returns:
            Configured AutomationClient instance

        Raises:
            ValidationError: If configuration is invalid or incomplete
        """
        profile = profile or self.profile
        url, email, api_token = self.get_credentials(profile)
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


def get_jira_client(profile: Optional[str] = None) -> JiraClient:
    """
    Convenience function to get a configured JIRA client.

    Args:
        profile: Profile name (default: from config or environment)

    Returns:
        Configured JiraClient instance (or MockJiraClient if JIRA_MOCK_MODE=true)

    Raises:
        ValidationError: If configuration is invalid or incomplete
    """
    # Check for mock mode first - allows testing without real JIRA credentials
    from .mock import is_mock_mode, MockJiraClient
    if is_mock_mode():
        return MockJiraClient()

    config_manager = ConfigManager.get_instance(profile=profile)
    return config_manager.get_client()


def get_automation_client(profile: Optional[str] = None) -> AutomationClient:
    """
    Convenience function to get a configured Automation API client.

    Args:
        profile: Profile name (default: from config or environment)

    Returns:
        Configured AutomationClient instance

    Raises:
        ValidationError: If configuration is invalid or incomplete
    """
    config_manager = ConfigManager.get_instance(profile=profile)
    return config_manager.get_automation_client()


def get_agile_fields(profile: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to get Agile field IDs.

    Args:
        profile: Profile name (default: from config or environment)

    Returns:
        Dictionary of field names to field IDs
    """
    config_manager = ConfigManager.get_instance(profile=profile)
    return config_manager.get_agile_fields()


def get_agile_field(field_name: str, profile: Optional[str] = None) -> str:
    """
    Convenience function to get a specific Agile field ID.

    Args:
        field_name: Field name (epic_link, story_points, epic_name, epic_color, sprint)
        profile: Profile name (default: from config or environment)

    Returns:
        Field ID string

    Raises:
        ValidationError: If field_name is not a valid Agile field
    """
    config_manager = ConfigManager.get_instance(profile=profile)
    return config_manager.get_agile_field(field_name)


# Project context functions - lazy imports to avoid circular dependencies
def get_project_context(project_key: str, profile: Optional[str] = None):
    """
    Convenience function to get project context.

    Lazy-loads project context from skill directory and/or settings.local.json.

    Args:
        project_key: JIRA project key (e.g., 'PROJ')
        profile: Profile name (default: from config or environment)

    Returns:
        ProjectContext object with metadata, workflows, patterns, and defaults
    """
    from project_context import get_project_context as _get_project_context

    return _get_project_context(project_key, profile)


def get_project_defaults(
    project_key: str, issue_type: Optional[str] = None, profile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to get default values for issue creation.

    Args:
        project_key: JIRA project key (e.g., 'PROJ')
        issue_type: Issue type name (e.g., 'Bug', 'Story') - if specified,
                    merges global defaults with type-specific defaults
        profile: Profile name (default: from config or environment)

    Returns:
        Dict with default values: priority, assignee, labels, components, etc.
        Returns empty dict if no project context exists.
    """
    from project_context import get_project_context as _get_project_context
    from project_context import get_defaults_for_issue_type

    context = _get_project_context(project_key, profile)

    if not context.has_context():
        return {}

    if issue_type:
        return get_defaults_for_issue_type(context, issue_type)
    else:
        return context.defaults.get("global", {})


def has_project_context(project_key: str, profile: Optional[str] = None) -> bool:
    """
    Convenience function to check if project context exists.

    Args:
        project_key: JIRA project key
        profile: Profile name (default: from config or environment)

    Returns:
        True if skill directory or settings config exists for this project
    """
    from project_context import has_project_context as _has_project_context

    return _has_project_context(project_key, profile)

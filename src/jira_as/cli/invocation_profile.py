"""Policy posture selected explicitly for one CLI invocation."""

import os
from contextvars import ContextVar, Token

_profile: ContextVar[str | None] = ContextVar("jira_as_cli_profile", default=None)


def select_profile(name: str | None) -> Token[str | None]:
    return _profile.set(name)


def reset_profile(token: Token[str | None]) -> None:
    _profile.reset(token)


def active_profile() -> str | None:
    return _profile.get()


def check_interactive_environment() -> None:
    """Do not let a human profile override an exported automation boundary."""
    from jira_as.error_handler import ValidationError

    if "JIRA_ALLOWED_PROJECTS" in os.environ:
        raise ValidationError(
            "--profile interactive cannot override JIRA_ALLOWED_PROJECTS; "
            "unset it outside the sandbox"
        )
    site = os.getenv("JIRA_ALLOW_SITE_OPERATIONS")
    if site is not None:
        normalized_site = site.strip().lower()
        if normalized_site == "false":
            raise ValidationError(
                "--profile interactive cannot override JIRA_ALLOW_SITE_OPERATIONS=false"
            )
        if normalized_site != "true":
            raise ValidationError("JIRA_ALLOW_SITE_OPERATIONS must be true or false")
    mode = os.getenv("JIRA_SCOPE_ENFORCEMENT")
    if mode is not None:
        normalized = mode.strip().lower()
        if normalized == "enforcing":
            raise ValidationError(
                "--profile interactive cannot override JIRA_SCOPE_ENFORCEMENT=enforcing"
            )
        if normalized != "permissive":
            raise ValidationError(
                "JIRA_SCOPE_ENFORCEMENT must be enforcing or permissive"
            )


def allowed_projects_for_cli() -> list[str] | None:
    """Resolve the legacy argv check under the selected invocation posture."""
    from jira_as.config_manager import ConfigManager

    if active_profile() == "interactive":
        check_interactive_environment()
        return None
    return ConfigManager.get_instance().get_allowed_projects()
